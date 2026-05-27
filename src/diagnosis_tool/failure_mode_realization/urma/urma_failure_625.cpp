#include "urma_failure_625.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure625> g_urma("urma_625");

bool UrmaFailure625::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure625::GetName() const
{
    return "URMA context、JFS对象无效导致释放JFS失败";
}

std::string UrmaFailure625::GetRootCauseDesc() const
{
    return "函数用于释放JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure625::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure625::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure625::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfs，Invalid parameter。";
}

std::string UrmaFailure625::GetId() const
{
    return "urma_625";
}

} // namespace diag
