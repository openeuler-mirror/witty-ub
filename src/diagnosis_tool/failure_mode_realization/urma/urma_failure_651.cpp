#include "urma_failure_651.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure651> g_urma("urma_651");

bool UrmaFailure651::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure651::GetName() const
{
    return "URMA context、provider操作表、provider未提供free_jfc操作实现无效导致释放JFC失败";
}

std::string UrmaFailure651::GetRootCauseDesc() const
{
    return "函数用于释放JFC，调用方传入的URMA "
           "context、provider操作表、provider未提供free_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure651::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure651::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure651::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfc，Invalid parameter.。";
}

std::string UrmaFailure651::GetId() const
{
    return "urma_651";
}

} // namespace diag
