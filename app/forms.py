#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask.ext.wtf import Form, TextField, PasswordField, BooleanField, FileField
from flask.ext.wtf import Required, Email, EqualTo, Length, file_allowed, file_required

class Signup_Form(Form):
    username = TextField('Username', validators = [Required(), Length(min=4, max=12)])
    password = PasswordField('Password', validators = [Length(min=6, max=24), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password')
    email = TextField('E-mail', validators = [Email()])
    accept_tos = BooleanField('I accept the terms', validators = [Required()])


class Upload_Form(Form):
    name = TextField('Name', validators = [Required(), Length(min=1, max=12)])
    img_file = FileField("Image", validators = [file_required()])
