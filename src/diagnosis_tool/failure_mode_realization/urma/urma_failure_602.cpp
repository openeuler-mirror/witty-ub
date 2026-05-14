#include "urma_failure_602.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure602> g_urma("urma_602");

bool UrmaFailure602::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_unimport_jetty_async' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to unimport jetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure602::GetName() const
{
    return "urma_unimport_jetty_async 执行导入 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure602::GetRootCauseDesc() const
{
    return "urma_unimport_jetty_async 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure602::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure602::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure602::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to unimport jetty";
}

std::string UrmaFailure602::GetId() const
{
    return "urma_602";
}

} // namespace diag
