#include "urma_failure_667.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure667> g_urma("urma_667");

bool UrmaFailure667::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure667::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure667::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure667::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure667::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure667::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Invalid parameter.。";
}

std::string UrmaFailure667::GetId() const
{
    return "urma_667";
}

} // namespace diag
