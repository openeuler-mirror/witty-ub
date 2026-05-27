#include "urma_failure_576.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure576> g_urma("urma_576");

bool UrmaFailure576::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_send' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'null pointer exists in tjfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure576::GetName() const
{
    return "投递WR过程中依赖步骤失败";
}

std::string UrmaFailure576::GetRootCauseDesc() const
{
    return "函数用于投递WR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure576::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure576::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure576::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_send，null pointer exists in tjfr.";
}

std::string UrmaFailure576::GetId() const
{
    return "urma_576";
}

} // namespace diag
