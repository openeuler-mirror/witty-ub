#include "urma_failure_153.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure153> g_urma("urma_153");

bool UrmaFailure153::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_active_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Jetty state is wrong in active_jetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure153::GetName() const
{
    return "urma_active_jetty 执行激活 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure153::GetRootCauseDesc() const
{
    return "urma_active_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure153::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure153::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure153::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Jetty state is wrong in active_jetty";
}

std::string UrmaFailure153::GetId() const
{
    return "urma_153";
}

} // namespace diag
