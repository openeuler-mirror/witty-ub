#include "urma_failure_836.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure836> g_urma("urma_836");

bool UrmaFailure836::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_advise_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure836::GetName() const
{
    return "URMA context、JFS对象无效导致释放JFR失败";
}

std::string UrmaFailure836::GetRootCauseDesc() const
{
    return "函数用于释放JFR，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure836::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure836::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure836::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_advise_jfr，Invalid parameter.";
}

std::string UrmaFailure836::GetId() const
{
    return "urma_836";
}

} // namespace diag
