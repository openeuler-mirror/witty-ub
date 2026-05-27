#include "urma_failure_028.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure028> g_urma("urma_028");

bool UrmaFailure028::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_init_member_eid_info_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get device by name'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure028::GetName() const
{
    return "获取设备过程中依赖步骤失败";
}

std::string UrmaFailure028::GetRootCauseDesc() const
{
    return "函数用于获取设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure028::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure028::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure028::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_init_member_eid_info_list，Failed to get device by name";
}

std::string UrmaFailure028::GetId() const
{
    return "urma_028";
}

} // namespace diag
