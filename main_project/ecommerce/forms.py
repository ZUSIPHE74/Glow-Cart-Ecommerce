from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Store, Product, Review, Profile


class UserRegistrationForm(UserCreationForm):
    """Form for user registration with account type selection and security questions"""
    ACCOUNT_TYPES = [
        ('buyer', 'Buyer'),
        ('vendor', 'Vendor'),
    ]
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPES, widget=forms.RadioSelect)
    security_question = forms.ChoiceField(choices=Profile.SECURITY_QUESTIONS, required=True)
    security_answer = forms.CharField(max_length=255, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'account_type', 'security_question', 'security_answer']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create profile
            Profile.objects.create(
                user=user,
                security_question=self.cleaned_data['security_question'],
                security_answer=self.cleaned_data['security_answer']
            )
        return user


class StoreForm(forms.ModelForm):
    """Form for creating/editing stores"""
    class Meta:
        model = Store
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ProductForm(forms.ModelForm):
    """Form for creating/editing products"""
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock_quantity', 'category', 'brand', 'condition', 'specifications', 'image', 'image_url']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'General product description...'}),
            'specifications': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Technical specifications, dimensions, etc.'}),
        }


class ReviewForm(forms.ModelForm):
    """Form for leaving reviews"""
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }


class CheckoutForm(forms.Form):
    """Form for checkout information"""
    shipping_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    
    PAYMENT_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('apple_pay', 'Apple Pay'),
    ]
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, widget=forms.RadioSelect, initial='apple_pay')
    
    card_number = forms.CharField(max_length=16, min_length=16, required=False, widget=forms.TextInput(attrs={'placeholder': '16-digit card number', 'class': 'form-control'}))
    expiry_date = forms.CharField(max_length=5, min_length=5, required=False, widget=forms.TextInput(attrs={'placeholder': 'MM/YY', 'class': 'form-control'}))
    cvv = forms.CharField(max_length=4, min_length=3, required=False, widget=forms.TextInput(attrs={'placeholder': 'CVV', 'class': 'form-control'}))

    confirm_purchase = forms.BooleanField(required=True, label="I confirm my purchase")

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        if payment_method == 'credit_card':
            if not cleaned_data.get('card_number') or not cleaned_data.get('expiry_date') or not cleaned_data.get('cvv'):
                raise forms.ValidationError("Please provide all card details (Card Number, Expiry, CVV) for Credit Card payment.")
        return cleaned_data