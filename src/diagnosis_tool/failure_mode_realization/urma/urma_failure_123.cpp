#include "urma_failure_123.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure123> g_urma("urma_123");

bool UrmaFailure123::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'output length too large, out.len=' | grep -F ', buf.len='");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure123::GetName() const
{
    return "获取JFR过程中依赖步骤失败";
}

std::string UrmaFailure123::GetRootCauseDesc() const
{
    return "函数用于获取JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure123::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure123::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure123::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfr_opt，output length too large, out.len=，, buf.len=。";
}

std::string UrmaFailure123::GetId() const
{
    return "urma_123";
}

} // namespace diag
