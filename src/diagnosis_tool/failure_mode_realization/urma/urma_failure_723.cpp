#include "urma_failure_723.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure723> g_urma("urma_723");

bool UrmaFailure723::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_set_bonding_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bonding mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure723::GetName() const
{
    return "URMA context、设备对象无效导致设置context失败";
}

std::string UrmaFailure723::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context、设备对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure723::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure723::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure723::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_set_bonding_mode，Invalid bonding mode:";
}

std::string UrmaFailure723::GetId() const
{
    return "urma_723";
}

} // namespace diag
