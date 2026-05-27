#include "urma_failure_669.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure669> g_urma("urma_669");

bool UrmaFailure669::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure669::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure669::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure669::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure669::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure669::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Invalid parameter, index:。";
}

std::string UrmaFailure669::GetId() const
{
    return "urma_669";
}

} // namespace diag
