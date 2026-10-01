from django import forms


class StyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            widget.attrs["class"] = "form-check-input" if isinstance(widget, forms.CheckboxInput) else "form-select" if isinstance(widget, forms.Select) else "form-control"

    def add_serializer_errors(self, errors):
        if isinstance(errors, dict):
            for key, values in errors.items():
                self.add_error(key if key in self.fields else None, [str(value) for value in values] if isinstance(values, list) else str(values))
        else:
            self.add_error(None, str(errors))


class LoginForm(StyledForm):
    email = forms.EmailField(label="E-mail", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password = forms.CharField(label="Senha", max_length=128, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class RegisterForm(LoginForm):
    password = forms.CharField(label="Senha", max_length=128, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), help_text="Use pelo menos 12 caracteres. Evite senhas comuns e semelhantes ao e-mail.")
    password_confirm = forms.CharField(label="Confirme a senha", max_length=128, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("password_confirm"):
            self.add_error("password_confirm", "As senhas não conferem.")
        return data
