#include "urma_failure_411.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure411> g_urma("urma_411");

bool UrmaFailure411::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_query_port' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid query port param.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure411::GetName() const
{
    return "URMA context无效导致查询端口失败";
}

std::string UrmaFailure411::GetRootCauseDesc() const
{
    return "函数用于查询端口，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure411::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure411::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure411::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_user_ctl_query_port，Invalid query port param.";
}

std::string UrmaFailure411::GetId() const
{
    return "urma_411";
}

} // namespace diag
