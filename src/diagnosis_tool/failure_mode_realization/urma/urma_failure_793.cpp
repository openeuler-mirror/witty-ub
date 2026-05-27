#include "urma_failure_793.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure793> g_urma("urma_793");

bool UrmaFailure793::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure793::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供modify_jfs操作实现无效导致修改JFS失败";
}

std::string UrmaFailure793::GetRootCauseDesc() const
{
    return "函数用于修改JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供modify_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure793::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure793::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure793::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfs，Invalid parameter.。";
}

std::string UrmaFailure793::GetId() const
{
    return "urma_793";
}

} // namespace diag
