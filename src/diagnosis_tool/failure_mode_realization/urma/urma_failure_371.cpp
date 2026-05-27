#include "urma_failure_371.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure371> g_urma("urma_371");

bool UrmaFailure371::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure371::GetName() const
{
    return "URMA context、JFS对象、JFR对象无效导致分配JFS失败";
}

std::string UrmaFailure371::GetRootCauseDesc() const
{
    return "函数用于分配JFS，调用方传入的URMA context、JFS对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure371::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure371::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure371::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfs，Invalid parameter。";
}

std::string UrmaFailure371::GetId() const
{
    return "urma_371";
}

} // namespace diag
