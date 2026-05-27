#include "urma_failure_588.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure588> g_urma("urma_588");

bool UrmaFailure588::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_post_jfs_wr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure588::GetName() const
{
    return "JFS对象、WR对象无效导致投递JFS失败";
}

std::string UrmaFailure588::GetRootCauseDesc() const
{
    return "函数用于投递JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure588::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure588::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure588::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_post_jfs_wr，Invalid parameter.。";
}

std::string UrmaFailure588::GetId() const
{
    return "urma_588";
}

} // namespace diag
