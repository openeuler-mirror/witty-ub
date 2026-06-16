#include "urma_failure_649.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure649> g_urma("urma_649");

bool UrmaFailure649::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure649::GetName() const
{
    return "URMA context、provider操作表无效导致释放JFC失败";
}

std::string UrmaFailure649::GetRootCauseDesc() const
{
    return "函数用于释放JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure649::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure649::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure649::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfc，Invalid parameter.。";
}

std::string UrmaFailure649::GetId() const
{
    return "urma_649";
}

} // namespace diag
