#include "urma_failure_807.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure807> g_urma("urma_807");

bool UrmaFailure807::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure807::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供deactive_jfs操作实现无效导致去激活JFS失败";
}

std::string UrmaFailure807::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供deactive_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure807::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure807::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure807::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，Invalid parameter.。";
}

std::string UrmaFailure807::GetId() const
{
    return "urma_807";
}

} // namespace diag
