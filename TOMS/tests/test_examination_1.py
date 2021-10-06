from odoo.tests.common import TransactionCase
from odoo.tests import tagged
# from odoo.tests import common

@tagged('-at_install', 'post_install')
class TestExamination(TransactionCase):
    """
        Tests for Customer Activity Statement.
    """

    def test_createdata(self):
        # Create a new project with the test
        test_clinic_exam = self.env['clinical.examination'].create({
            'partner_id': 4
        })
        print("testtest")

        # Check if the project name and the task name match
        # self.assertEqual(test_clinic_exam, 'TestProject')
        # self.assertEqual(test_project_task.name, 'ExampleTask')
        # Check if the project assigned to the task is in fact the correct id
        # self.assertEqual(test_project_task.project_id.id, test_project.id)
        # Do a little print to show it visually for this demo - in production you don't really need this.
        print('Your test was succesfull!', test_clinic_exam)


    # def setUp(self):
    #     super(TestExamination, self).setUp()
    #     print('\n\======call')
    #     self.clinic = self.env['clinical.examination']
    #
    #     # create an employee record
    #     self.employee1 = self.employee.create({
    #         'name': 'Employee 1',
    #         'date_of_birth': '1990-04-18',
    #         'address': 'Ahmedabad, india',
    #         'email': 'employee1@gmail.com',
    #         'experience': 0.5,
    #         'department': 'accounting'
    #     })

