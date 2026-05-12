interface Props {
  message: string;
}

const ErrorMessage = ({ message }: Props) => (
  <div className="error">
    <strong>Could not load data.</strong> {message}
  </div>
);

export default ErrorMessage;
