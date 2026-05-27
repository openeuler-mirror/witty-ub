#include "urma_failure_751.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure751> g_urma("urma_751");

bool UrmaFailure751::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfc not exist in jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure751::GetName() const
{
    return "设置JFC过程中依赖步骤失败";
}

std::string UrmaFailure751::GetRootCauseDesc() const
{
    return "函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure751::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure751::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure751::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jfr_opt，jfc not exist in jfr.";
}

std::string UrmaFailure751::GetId() const
{
    return "urma_751";
}

} // namespace diag
