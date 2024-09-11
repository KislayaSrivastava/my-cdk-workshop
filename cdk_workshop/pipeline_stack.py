from aws_cdk import Stack # type: ignore
from constructs import Construct # type: ignore
from aws_cdk.aws_codecommit import Repository # type: ignore
from aws_cdk.pipelines import ( # type: ignore
    CodePipeline,
    CodePipelineSource,
    ShellStep,
    CodeBuildStep
)
from aws_cdk.aws_codebuild import ( # type: ignore
    BuildEnvironment,
    LinuxBuildImage,
    ComputeType
)
from cdk_workshop.deploy_stage import DeployStage

class PipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        environment_type = self.node.try_get_context("environmentType")
        if not environment_type:
            environment_type = "qa"

        self.context = self.node.try_get_context(environment_type)

        repository = Repository.from_repository_arn(
            self,
            "CodeCommitRepo",
            f'arn:aws:codecommit:{self.region}:{self.account}:{self.context["repository"]["name"]}'
        )

        self.source_stage = CodePipelineSource.code_commit(repository,self.context["repository"]["branch"])

        pipeline = CodePipeline(self, "Pipeline",
            pipeline_name = self.context["pipeline"]["name"],
            synth = ShellStep(
                "Synth",
                input = self.source_stage,
                env={
                    "ENV_TYPE" : environment_type
                },
                install_commands=[
                    "npm install -g aws-cdk",
                    "pip3 install -r requirements.txt",
                    "pip3 install -r requirements-dev.txt",
                    "ACCOUNT=$(aws sts get-caller-identity | jq -r .Account)"
                    ],
                commands=[
                    "cdk synth -c account=$ACCOUNT -c environmentType=$ENV_TYPE"
                    ],
            )
        )

        quality_steps = self.create_code_quality_steps()

        pipeline.add_stage(
            DeployStage(
                scope = self,
                construct_id ='QA',
                environment_type = "qa"
            ),
            pre = quality_steps
        )

    def create_code_quality_steps(self):
        steps = []

        environment = BuildEnvironment(
            build_image = LinuxBuildImage.STANDARD_7_0,
            compute_type = ComputeType.SMALL,
            privileged = True
        )

        steps.append(
            CodeBuildStep(
                "GitSecrets",
                input=self.source_stage,
                build_environment = environment,
                project_name = "cdk-pipelines-git-secrets",
                install_commands = [
                    "SECRETS_FOLDER=git-secrets",
                    "mkdir $SECRETS_FOLDER",
                    "git clone --quiet https://github.com/awslabs/git-secrets.git $SECRETS_FOLDER",
                    "cd $SECRETS_FOLDER",
                    "make install",
                    "cd .. && rm -rf $SECRETS_FOLDER"
                ],
                commands = [
                    "git secrets --register-aws",
                    "git secrets --scan",
                    "echo No vulnerabilites detected. Have a really nice day!"
                ]
            )
        )

        return steps
