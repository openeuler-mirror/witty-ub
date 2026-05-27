#include "urma_failure_396.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure396> g_urma("urma_396");

bool UrmaFailure396::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure396::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfs操作实现无效导致分配JFS失败";
}

std::string UrmaFailure396::GetRootCauseDesc() const
{
    return "函数用于分配JFS，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure396::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure396::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure396::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfs，Invalid parameter.。";
}

std::string UrmaFailure396::GetId() const
{
    return "urma_396";
}

} // namespace diag
