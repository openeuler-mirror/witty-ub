#include "urma_failure_773.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure773> g_urma("urma_773");

bool UrmaFailure773::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure773::GetName() const
{
    return "URMA context、provider操作表、provider未提供modify_jfc操作实现无效导致修改JFC失败";
}

std::string UrmaFailure773::GetRootCauseDesc() const
{
    return "函数用于修改JFC，调用方传入的URMA "
           "context、provider操作表、provider未提供modify_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure773::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure773::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure773::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfc，Invalid parameter.。";
}

std::string UrmaFailure773::GetId() const
{
    return "urma_773";
}

} // namespace diag
