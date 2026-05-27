#include "urma_failure_658.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure658> g_urma("urma_658");

bool UrmaFailure658::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure658::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表无效导致删除JFC失败";
}

std::string UrmaFailure658::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure658::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure658::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure658::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc_batch，Invalid parameter, index:。";
}

std::string UrmaFailure658::GetId() const
{
    return "urma_658";
}

} // namespace diag
