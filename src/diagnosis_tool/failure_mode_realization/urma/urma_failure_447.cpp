#include "urma_failure_447.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure447> g_urma("urma_447");

bool UrmaFailure447::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec urma_jetty_set_options'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure447::GetName() const
{
    return "urma_set_jetty_opt 执行设置 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure447::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure447::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure447::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure447::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to exec urma_jetty_set_options";
}

std::string UrmaFailure447::GetId() const
{
    return "urma_447";
}

} // namespace diag
