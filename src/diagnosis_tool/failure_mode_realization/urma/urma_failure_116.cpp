#include "urma_failure_116.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure116> g_urma("urma_116");

bool UrmaFailure116::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'output length too large, out.len=' | grep -F ', buf.len='");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure116::GetName() const
{
    return "获取JFC过程中依赖步骤失败";
}

std::string UrmaFailure116::GetRootCauseDesc() const
{
    return "函数用于获取JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure116::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure116::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure116::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_jfc_opt，output length too large, out.len=，, buf.len=";
}

std::string UrmaFailure116::GetId() const
{
    return "urma_116";
}

} // namespace diag
