#include "urma_failure_582.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure582> g_urma("urma_582");

bool UrmaFailure582::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_send' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'null pointer exists in tjfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure582::GetName() const
{
    return "投递WR过程中依赖步骤失败";
}

std::string UrmaFailure582::GetRootCauseDesc() const
{
    return "函数用于投递WR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure582::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure582::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure582::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_send，null pointer exists in tjfr.。";
}

std::string UrmaFailure582::GetId() const
{
    return "urma_582";
}

} // namespace diag
