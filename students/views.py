from django.urls import reverse, reverse_lazy
from django.contrib.auth import login
from django.shortcuts import render
from .forms import (
    StudentProfileCreateForm,
    CourseEnrollForm
)
from django.views.generic.edit import (
    CreateView,
    UpdateView,
    DeleteView,
     FormView

)
from accounts.forms import UserCreateForm
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .models import StudentProfile
from courses.models import Course
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect

from django.contrib import messages
from accounts.models import User
import csv
from io import StringIO
#Create Student Profile




# Create your views here.


# Students Profile


def register(request):
    if request.method == 'POST':
        user_form = UserCreateForm(data=request.POST)
        profile_form = StudentProfileCreateForm(
            data = request.POST,
            files = request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.student = True
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user # set the user created to the profile
            if 'mugshot' in request.FILES:
                profile.mugshot = request.FILES['mugshot']
            profile.save()
            return HttpResponseRedirect(reverse('students_profile:student_profile_list'))
    else:
        user_form = UserCreateForm()
        profile_form = StudentProfileCreateForm()
    return render(request,'students/profile/create_form.html', {
        'user_form':user_form,
        'profile_form':profile_form
    })


class StudentListProfileView(ListView):
    model = StudentProfile
    context_object_name = 'students'
    template_name = 'students/students_list/list.html'
    ordering = ['-student_class']



class StudentDetailProfileView(DetailView):
    model = StudentProfile
    context_object_name = 'student_details'
    template_name = 'students/profile/dashboard.html'


class StudentUpdateProfileView(UpdateView):
    model = StudentProfile
    template_name = 'students/profile/profile_form.html'
    form_class = StudentProfileCreateForm
    
    # def get_success_url(self):
    #     return HttpResponseRedirect(reverse('students_profile:student_profile_detail', args=[self.object.id]))




class StudentDeleteProfileView(DeleteView):
    model = StudentProfile
    success_url = reverse_lazy('students_profile:student_profile_list')
    template_name = 'students/profile/delete.html'





class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    course = None
    form_class = CourseEnrollForm
    template_name = 'course/courses/detail.html'


    def form_valid(self, form):
        self.course = form.cleaned_data['course']
        self.course.students.add(self.request.user)
        # StudentProfile.objects.get(user=self.request.user)
        return super(StudentEnrollCourseView,self).form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('student_course_detail', args=[self.course.id])




# Course Students Are Enrolled in
class StudentCourseList(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'students/course/list.html'

    def get_queryset(self):
        qs = super(StudentCourseList, self).get_queryset()
        return qs.filter(students__in=[StudentProfile.objects.get(user=self.request.user)])
        # self.request.user
        

class StudentCourseDetailView(DetailView):
    model = Course
    template_name = 'students/course/detail.html'

    def get_queryset(self):
        # Use self.__class__ instead of a non-existent class name
        qs = super(StudentCourseDetailView, self).get_queryset()
        # Use StudentProfile to get the current user's profile
        return qs.filter(students__in=[self.request.user.studentprofile])
    
    def get_context_data(self, **kwargs):
        # Use self.__class__ instead of a non-existent class name
        context = super(StudentCourseDetailView, self).get_context_data(**kwargs)
        
        # get course object
        course = self.get_object()
        if 'module_id' in self.kwargs:
            # get current module
            context['module'] = course.modules.get(
                id=self.kwargs['module_id']
            )
        else:
            # Handle case where there are no modules
            context['module'] = course.modules.first() if course.modules.exists() else None
        return context

def upload_student(request):
    '''
    View for uploading Students via CSV
    '''
    template_name = 'students/profile/upload.html'
    
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'studentprofile' not in request.FILES:
            messages.error(request, "No file uploaded")
            return render(request, template_name)

        csvfile = request.FILES['studentprofile']
        
        # Validate file type
        if not csvfile.name.endswith('.csv'):
            messages.error(request, "CSV file format not supported")
            return render(request, template_name)

        try:
            # Read the CSV file
            file_data = csvfile.read().decode('utf-8')
            csv_data = csv.reader(StringIO(file_data))
            
            # Track successful and failed imports
            successful_imports = 0
            failed_imports = 0

            # Skip header row if exists
            next(csv_data, None)

            for row in csv_data:
                # Skip empty rows
                if not row:
                    continue

                try:
                    # Ensure we have enough fields
                    if len(row) < 11:
                        messages.warning(request, f"Skipping incomplete row: {row}")
                        failed_imports += 1
                        continue

                    # Create user
                    user = User.objects.create_user(
                        email=row[0].strip(),
                        password=row[1].strip()
                    )
                    user.student = True
                    user.save()

                    # Create student profile
                    StudentProfile.objects.create(
                        user=user,
                        first_name=row[2].strip(),
                        other_name=row[3].strip(),
                        last_name=row[4].strip(),
                        gender=row[5].strip(),
                        # Note: You might need to handle file uploads differently
                        # mugshot=row[6].strip(),  
                        student_class=row[7].strip(),
                        date_of_birth=row[9].strip(),
                        date_admitted=row[9].strip(),
                        address=row[10].strip()
                    )
                    successful_imports += 1

                except Exception as e:
                    messages.error(request, f"Error importing student: {str(e)}")
                    failed_imports += 1

            # Summary message
            messages.success(request, 
                f"Import complete. "
                f"Successful imports: {successful_imports}, "
                f"Failed imports: {failed_imports}"
            )

        except Exception as e:
            messages.error(request, f"Error processing CSV file: {str(e)}")

    return render(request, template_name, {})