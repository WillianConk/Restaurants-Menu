from cgi import escape
from google.auth.transport import requests
from google.oauth2 import id_token
from database_setup import Base, Restaurant, MenuItem
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, asc
from flask import Flask, render_template, request, redirect
from flask import jsonify, url_for, flash, session as user_session
app = Flask(__name__)


# Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenu.db',
                       connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# JSON APIs to view Restaurant Information
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    if isUserLogged():
        restaurant = session.query(Restaurant).filter_by(
            id=restaurant_id, user_id=user_session['user']['email']).one()
        items = session.query(MenuItem).filter_by(
                    restaurant_id=restaurant_id,
                    user_id=user_session['user']['email']).all()
        return jsonify(MenuItems=[i.serialize for i in items])
    else:
        return "Unauthorized"


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    if isUserLogged():
        Menu_Item = session.query(MenuItem).filter_by(
            id=menu_id, user_id=user_session['user']['email']).one()
        return jsonify(Menu_Item=Menu_Item.serialize)
    else:
        return "Unauthorized"


@app.route('/restaurant/JSON')
def restaurantsJSON():
    if isUserLogged():
        # Display all your restaurants in JSON format
        restaurants = session.query(Restaurant).filter_by(
            user_id=user_session['user']['email'])
        return jsonify(restaurants=[r.serialize for r in restaurants])
    else:
        return "Unauthorized"


# Show all restaurants
@app.route('/')
@app.route('/restaurant/')
def showRestaurants():

    if isUserLogged():
        user = "Welcome " + \
            user_session['user']['name'] + " <a href='/logout'>( Logout )</a>"
    else:
        user = "<a href='/login'> Login </a>"

    restaurants = session.query(Restaurant).order_by(asc(Restaurant.name))

    return render_template(
        'restaurants.html', restaurants=restaurants,
        user=user,  logged_in=isUserLogged())


# Create a new restaurant
@app.route('/restaurant/new/', methods=['GET', 'POST'])
def newRestaurant():
    if isUserLogged():
        if request.method == 'POST':
            newRestaurant = Restaurant(
                name=request.form['name'],
                user_id=user_session['user']['email'])
            session.add(newRestaurant)
            flash('New Restaurant %s Successfully Created' %
                  newRestaurant.name)
            session.commit()
            return redirect(url_for('showRestaurants'))
        else:
            return render_template('newRestaurant.html')

    else:
        return "Unauthorized"


def isUserLogged():
    try:
        user_session['user']
    except Exception as e:
        print(e)
        return False
    else:
        return True


# Edit a restaurant
@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):

    # User can only edit a restaurant if he owns it.
    if isUserLogged():
        try:
            editedRestaurant = session.query(Restaurant).filter_by(
                id=restaurant_id, user_id=user_session['user']['email']).one()
        except Exception as e:
            print(e)
            return redirect('/')

        if request.method == 'POST':
            if request.form['name']:
                editedRestaurant.name = request.form['name']
                flash('Restaurant Successfully Edited %s' %
                      editedRestaurant.name)
                return redirect(url_for('showRestaurants'))
        else:
            return render_template(
                'editRestaurant.html', restaurant=editedRestaurant)
    else:
        return "Unauthorized"


@app.route('/logout', methods=["GET"])
def logout():
    del user_session['user']
    return redirect('/')


# Delete a restaurant
@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    if isUserLogged():

            # If user does not own the restaurant, he cannot delete it.
        try:
            restaurantToDelete = session.query(Restaurant).filter_by(
                id=restaurant_id, user_id=user_session['user']['email']).one()
        except Exception as e:
            print(e)
            return redirect('/')

        if request.method == 'POST':
            session.delete(restaurantToDelete)
            flash('%s Successfully Deleted' % restaurantToDelete.name)
            session.commit()
            return redirect(url_for(
                'showRestaurants', restaurant_id=restaurant_id))
        else:
            return render_template(
                'deleteRestaurant.html', restaurant=restaurantToDelete)
    else:
        return "Unauthorized"


# Show a restaurant menu
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    if isUserLogged():
        logged_user = user_session['user']['email']
    else:
        logged_user = False

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return render_template(
        'menu.html', items=items, restaurant=restaurant, user_id=logged_user)


# Create a new menu item
@app.route(
    '/restaurant/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if isUserLogged():

        # If user does not own the restaurant,
        # he cannot create a menu item inside it.
        try:
            restaurant = session.query(Restaurant).filter_by(
                id=restaurant_id, user_id=user_session['user']['email']).one()
        except Exception as e:
            print(e)
            return redirect('/')

        if request.method == 'POST':
            newItem = MenuItem(
                name=request.form['name'],
                description=request.form['description'],
                user_id=user_session['user']
                ['email'], price=request.form['price'],
                course=request.form['course'], restaurant_id=restaurant_id)
            session.add(newItem)
            session.commit()
            flash('New Menu %s Item Successfully Created' % (newItem.name))
            return redirect(url_for('showMenu', restaurant_id=restaurant_id))
        else:
            return render_template(
                'newmenuitem.html', restaurant_id=restaurant_id)
    else:
        return "Unauthorized"


# Edit a menu item
@app.route(
    '/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit',
    methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):

    if isUserLogged():

        # If user is not the owner of the menu item, redirect him.
        try:
            editedItem = session.query(MenuItem).filter_by(
                id=menu_id, user_id=user_session['user']['email']).one()
            restaurant = session.query(Restaurant).filter_by(
                id=restaurant_id, user_id=user_session['user']['email']).one()
        except Exception as e:
            print(e)
            return redirect('/')

        if request.method == 'POST':
            if request.form['name']:
                editedItem.name = request.form['name']
            if request.form['description']:
                editedItem.description = request.form['description']
            if request.form['price']:
                editedItem.price = request.form['price']
            if request.form['course']:
                editedItem.course = request.form['course']
            session.add(editedItem)
            session.commit()
            flash('Menu Item Successfully Edited')
            return redirect(url_for('showMenu', restaurant_id=restaurant_id))
        else:
            return render_template(
                'editmenuitem.html', restaurant_id=restaurant_id,
                menu_id=menu_id, item=editedItem)
    else:
        return "Unauthorized"


# Delete a menu item
@app.route(
    '/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete',
    methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    if isUserLogged():

        # If user is not the owner of the menu item, redirect him.
        try:
            restaurant = session.query(Restaurant).filter_by(
                id=restaurant_id, user_id=user_session['user']['email']).one()
            itemToDelete = session.query(MenuItem).filter_by(
                id=menu_id, user_id=user_session['user']['email']).one()
        except Exception as e:
            print(e)
            return redirect('/')

        if request.method == 'POST':
            session.delete(itemToDelete)
            session.commit()
            flash('Menu Item Successfully Deleted')
            return redirect(url_for('showMenu', restaurant_id=restaurant_id))
        else:
            return render_template('deleteMenuItem.html', item=itemToDelete)
    else:
        return "Unauthorized"


# User Login
@app.route('/login', methods=['GET', 'POST'])
def userLogin():
    if not isUserLogged():
        if request.method == 'GET':
            return render_template('login.html')
        elif request.method == 'POST':

            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                idinfo = id_token.verify_oauth2_token(
                    request.form['token'], requests.Request(),
                    "107468542942-18du2vvplbk22cmjil63g16tis4jth6o"
                    ".apps.googleusercontent.com")

                if idinfo['iss'] not in [
                        'accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Wrong issuer.')
                userid = idinfo['sub']
                user_session['user'] = idinfo
                return redirect('/')

            except ValueError:
                # Invalid token
                pass
    else:
        return redirect('/')


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = False
    app.run(host='0.0.0.0', port=5000)
