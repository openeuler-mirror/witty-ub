#include "urma_failure_471.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure471> g_urma("urma_471");

bool UrmaFailure471::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_user_ctl' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to excecute user_ctl, ret')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure471::GetName() const
{
    return "urma_user_ctl 执行处理 URMA 对象 失败导致当前资源状态无法推进";
}

std::string UrmaFailure471::GetRootCauseDesc() const
{
    return "urma_user_ctl 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure471::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure471::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure471::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to excecute user_ctl, ret";
}

std::string UrmaFailure471::GetId() const
{
    return "urma_471";
}

} // namespace diag
