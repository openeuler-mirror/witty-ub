#include "urma_failure_134.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure134> g_urma("urma_134");

bool UrmaFailure134::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_bind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Not allowed to bind local jetty:' | "
        "grep -F 'of mode:' | "
        "grep -F ', with remote jetty:' | "
        "grep -F 'of mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure134::GetName() const
{
    return "urma_bind_jetty 执行绑定 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure134::GetRootCauseDesc() const
{
    return "urma_bind_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure134::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure134::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure134::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Not allowed to bind local jetty:, with remote jetty";
}

std::string UrmaFailure134::GetId() const
{
    return "urma_134";
}

} // namespace diag
