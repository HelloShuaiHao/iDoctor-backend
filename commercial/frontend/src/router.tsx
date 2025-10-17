import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ROUTES } from '@utils/constants';

// Pages
import HomePage from '@pages/HomePage';
import AuthPage from '@pages/AuthPage';
import DashboardPage from '@pages/DashboardPage';
import SubscriptionPage from '@pages/SubscriptionPage';
import MySubscriptionPage from '@pages/MySubscriptionPage';
import PaymentPage from '@pages/PaymentPage';
import ApiKeysPage from '@pages/ApiKeysPage';
import UsageStatsPage from '@pages/UsageStatsPage';

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
    path: ROUTES.MY_SUBSCRIPTION,
    element: <MySubscriptionPage />,
  },
  {
    path: ROUTES.PAYMENT,
    element: <PaymentPage />,
  },
  {
    path: ROUTES.API_KEYS,
    element: <ApiKeysPage />,
  },
  {
    path: ROUTES.USAGE_STATS,
    element: <UsageStatsPage />,
  },
  {
    path: '*',
    element: <Navigate to={ROUTES.HOME} replace />,
  },
]);
