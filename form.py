from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, NumberRange


class LoginForm(FlaskForm):
    email = StringField('อีเมล', validators=[DataRequired(), Email()])
    password = PasswordField('รหัสผ่าน', validators=[DataRequired()])
    submit = SubmitField('เข้าสู่ระบบ')


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    user_type = SelectField('User Type', choices=[('admin', 'Admin'), ('driver', 'Driver')], validators=[DataRequired()])
    license = StringField('License')
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    

class CustomerForm(FlaskForm):
    first_name = StringField('ชื่อ', validators=[DataRequired()])
    last_name = StringField('นามสกุล', validators=[DataRequired()])
    address = StringField('ที่อยู่', validators=[DataRequired()])
    phone = StringField('โทรศัพท์', validators=[DataRequired(), Regexp(r'^\d{10}$', message="หมายเลขโทรศัพท์ต้องมี 10 หลัก")])
    coordinate = StringField('พิกัด', validators=[DataRequired()])
    latitude = StringField('ละติจูด', validators=[DataRequired()])
    longitude = StringField('ลองจิจูด', validators=[DataRequired()])
    submit = SubmitField('ส่งข้อมูล')

class ProductForm(FlaskForm):
    brand = StringField('ยี่ห้อ', validators=[DataRequired()])
    weight_per_bag = FloatField('น้ำหนักต่อถุง (กก.)', validators=[DataRequired(), NumberRange(min=0)])
    price = FloatField('ราคา', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('ส่งข้อมูล')
