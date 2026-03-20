# Formulários do backoffice (cadastro de colaborador, departamento, jornada)
from django import forms
from django.contrib.auth import get_user_model
from .models import Profile, Departamento, Jornada

User = get_user_model()

INPUT_CLASS = 'w-full px-3 py-2 border border-slate-300 rounded-lg'


class DepartamentoForm(forms.ModelForm):
    """Formulário para criar/editar Departamento (usado nos dropdowns do colaborador)."""
    class Meta:
        model = Departamento
        fields = ['nome', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex: Vendas, TI, RH', 'class': INPUT_CLASS}),
            'ativo': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300'}),
        }


class JornadaForm(forms.ModelForm):
    """Formulário para criar/editar Jornada (usado nos dropdowns do colaborador)."""
    class Meta:
        model = Jornada
        fields = ['nome', 'tipo', 'hora_entrada_planejada', 'hora_saida_planejada', 'hora_inicio_intervalo', 'hora_fim_intervalo', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex: Vendas 08h-18h', 'class': INPUT_CLASS}),
            'tipo': forms.Select(attrs={'class': INPUT_CLASS}),
            'hora_entrada_planejada': forms.TimeInput(attrs={'type': 'time', 'class': INPUT_CLASS}),
            'hora_saida_planejada': forms.TimeInput(attrs={'type': 'time', 'class': INPUT_CLASS}),
            'hora_inicio_intervalo': forms.TimeInput(attrs={'type': 'time', 'class': INPUT_CLASS}),
            'hora_fim_intervalo': forms.TimeInput(attrs={'type': 'time', 'class': INPUT_CLASS}),
            'ativo': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300'}),
        }


class ColaboradorForm(forms.ModelForm):
    """Formulário completo para cadastrar/editar colaborador."""
    email = forms.EmailField(label='Email', required=True)
    password = forms.CharField(
        label='Palavra-passe',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='Deixe em branco para não alterar (ao editar).'
    )
    acesso_backoffice = forms.BooleanField(
        label='Acesso ao Backoffice',
        required=False,
        help_text='Se sim, o colaborador poderá entrar em /backoffice/ como administrador.'
    )

    class Meta:
        model = Profile
        fields = ['nome', 'endereco', 'data_nascimento', 'departamento', 'jornada']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome completo', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'endereco': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Morada completa', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'departamento': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'jornada': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
        }

    def __init__(self, *args, **kwargs):
        self.edit_user = kwargs.pop('edit_user', None)
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.filter(ativo=True).order_by('nome')
        self.fields['jornada'].queryset = Jornada.objects.filter(ativo=True).order_by('nome')
        self.fields['email'].widget.attrs['class'] = 'w-full px-3 py-2 border border-slate-300 rounded-lg'
        self.fields['password'].widget.attrs['class'] = 'w-full px-3 py-2 border border-slate-300 rounded-lg'
        if self.edit_user:
            self.fields['email'].initial = self.edit_user.email
            self.fields['email'].disabled = True
            self.fields['acesso_backoffice'].initial = self.edit_user.is_staff
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = 'Senha para o colaborador aceder ao sistema de ponto.'

    def save(self, commit=True):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        acesso_backoffice = self.cleaned_data.get('acesso_backoffice', False)

        if self.edit_user:
            profile = super().save(commit=False)
            user = self.edit_user
            if password:
                user.set_password(password)
            user.is_staff = acesso_backoffice
            user.save()
            if commit:
                profile.save()
            return profile
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password or User.objects.make_random_password(),
                is_staff=acesso_backoffice,
            )
            profile = super().save(commit=False)
            profile.user = user
            if commit:
                profile.save()
            return profile
