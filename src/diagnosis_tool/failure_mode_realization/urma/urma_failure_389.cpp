#include "urma_failure_389.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure389> g_urma("urma_389");

bool UrmaFailure389::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure389::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfc操作实现无效导致分配JFC失败";
}

std::string UrmaFailure389::GetRootCauseDesc() const
{
    return "函数用于分配JFC，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_"
           "jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure389::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure389::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure389::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfc，Invalid parameter.。";
}

std::string UrmaFailure389::GetId() const
{
    return "urma_389";
}

} // namespace diag
