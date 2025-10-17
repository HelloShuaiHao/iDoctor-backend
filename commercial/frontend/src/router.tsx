import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ROUTES } from '@utils/constants';

// Pages
import HomePage from '@pages/HomePage';
import AuthPage from '@pages/AuthPage';
import DashboardPage from '@pages/DashboardPage';
import SubscriptionPage from '@pages/SubscriptionPage';
import PaymentPage from '@pages/PaymentPage';

export const router = createBrowserRouter([
  {
    path: ROUTES.HOME,
    element: <HomePage />,
  },
  {
    path: ROUTES.LOGIN,
    element: <AuthPage mode="login" />,
  },
  {
    path: ROUTES.REGISTER,
    element: <AuthPage mode="register" />,
  },
  {
    path: ROUTES.DASHBOARD,
    element: <DashboardPage />,
  },
  {
    path: ROUTES.SUBSCRIPTION,
    element: <SubscriptionPage />,
  },
  {
    path: ROUTES.PAYMENT,
    element: <PaymentPage />,
  },
  {
    path: '*',
    element: <Navigate to={ROUTES.HOME} replace />,
  },
]);
