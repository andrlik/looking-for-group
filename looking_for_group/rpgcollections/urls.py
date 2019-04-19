from django.urls import path

from . import views


app_name = "rpgcollections"

urlpatterns = [
    path("books/add/", view=views.BookCreate.as_view(), name="add-book"),
    path("books/<slug:book>/", view=views.BookDetail.as_view(), name="book-detail"),
    path("books/<slug:book>/edit/", view=views.BookUpdate.as_view(), name="edit-book"),
    path(
        "books/<slug:book>/remove/", view=views.BookDelete.as_view(), name="remove book"
    ),
]
