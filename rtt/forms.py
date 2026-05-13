# Formulários do backoffice (cadastro de colaborador, departamento, jornada)
from django import forms
from django.contrib.auth import get_user_model
from .models import Profile, Departamento, Jornada, Viatura, RegistroKM, Marcacao

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
        fields = ['nome', 'endereco', 'data_nascimento', 'departamento', 'viatura']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome completo', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'endereco': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Morada completa', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'departamento': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
            'viatura': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg'}),
        }

    def __init__(self, *args, **kwargs):
        self.edit_user = kwargs.pop('edit_user', None)
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.filter(ativo=True).order_by('nome')
        self.fields['viatura'].queryset = Viatura.objects.filter(ativo=True).order_by('matricula')
        self.fields['email'].widget.attrs['class'] = 'w-full px-3 py-2 border border-slate-300 rounded-lg'
        self.fields['password'].widget.attrs['class'] = 'w-full px-3 py-2 border border-slate-300 rounded-lg'
        if self.edit_user:
            self.fields['email'].initial = self.edit_user.email
            self.fields['email'].disabled = True
            self.fields['acesso_backoffice'].initial = self.edit_user.is_staff
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = 'Senha para o colaborador aceder ao sistema de ponto.'

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not self.edit_user:
            if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
                raise forms.ValidationError("Este email já está registado no sistema.")
        return email

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


class ViaturaForm(forms.ModelForm):
    """Formulário para criar/editar Viaturas."""
    colaborador_atual = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Colaborador a utilizar",
        widget=forms.Select(attrs={'class': INPUT_CLASS})
    )

    class Meta:
        model = Viatura
        fields = ['matricula', 'marca_modelo', 'km_inicial', 'km_atual', 'colaborador_atual', 'ativo']
        widgets = {
            'matricula': forms.TextInput(attrs={'placeholder': 'Ex: 00-AA-00', 'class': INPUT_CLASS}),
            'marca_modelo': forms.TextInput(attrs={'placeholder': 'Ex: Renault Clio', 'class': INPUT_CLASS}),
            'km_inicial': forms.NumberInput(attrs={'class': INPUT_CLASS}),
            'km_atual': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': 'KM atual da viatura'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['colaborador_atual'].queryset = User.objects.filter(profile__isnull=False).order_by('profile__nome')
        # Sobrescrever o rótulo exibido para cada opção para usar o nome do perfil
        self.fields['colaborador_atual'].label_from_instance = lambda obj: obj.profile.nome or obj.email


class RegistroKMForm(forms.ModelForm):
    """Formulário para o administrador lançar KM manualmente."""
    class Meta:
        model = RegistroKM
        fields = ['utilizador', 'viatura', 'km', 'descricao']
        widgets = {
            'utilizador': forms.Select(attrs={'class': INPUT_CLASS}),
            'viatura': forms.Select(attrs={'class': INPUT_CLASS}),
            'km': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': 'KM Atual'}),
            'descricao': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Descrição opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['utilizador'].queryset = User.objects.filter(profile__isnull=False).order_by('profile__nome')
        self.fields['viatura'].queryset = Viatura.objects.filter(ativo=True).order_by('matricula')

class MarcacaoForm(forms.ModelForm):
    """Formulário para editar marcações de ponto manualmente."""
    data = forms.DateField(label='Data', widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))
    hora = forms.TimeField(label='Hora', widget=forms.TimeInput(attrs={'type': 'time', 'class': INPUT_CLASS}))

    class Meta:
        model = Marcacao
        fields = ['tipo', 'justificativa', 'aprovado']
        widgets = {
            'tipo': forms.Select(attrs={'class': INPUT_CLASS}),
            'justificativa': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Motivo da alteração', 'class': INPUT_CLASS}),
            'aprovado': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            from django.utils import timezone
            # Converter timestamp para local time antes de exibir no form
            dt = timezone.localtime(self.instance.timestamp)
            self.fields['data'].initial = dt.date()
            self.fields['hora'].initial = dt.time()

    def save(self, commit=True):
        from django.utils import timezone
        import datetime
        data = self.cleaned_data['data']
        hora = self.cleaned_data['hora']
        # Combinar data e hora e tornar aware
        dt = datetime.datetime.combine(data, hora)
        self.instance.timestamp = timezone.make_aware(dt)
        return super().save(commit=commit)
