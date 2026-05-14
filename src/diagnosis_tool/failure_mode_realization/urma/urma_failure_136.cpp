#include "urma_failure_136.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure136> g_urma("urma_136");

bool UrmaFailure136::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_bind_jetty_ex' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Not allowed to bind local jetty: of mode: with remote jetty: of mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure136::GetName() const
{
    return "urma_bind_jetty_ex 执行绑定 目标 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure136::GetRootCauseDesc() const
{
    return "urma_bind_jetty_ex 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure136::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure136::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure136::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Not allowed to bind local jetty: of mode: with remote jetty: of mode";
}

std::string UrmaFailure136::GetId() const
{
    return "urma_136";
}

} // namespace diag
