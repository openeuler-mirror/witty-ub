#include "urma_failure_028.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure028> g_urma("urma_028");

bool UrmaFailure028::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_init_member_eid_info_list' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Invalid slave device number' | grep -F 'of device'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure028::GetName() const
{
    return "设备对象无效导致初始化设备失败";
}

std::string UrmaFailure028::GetRootCauseDesc() const
{
    return "函数用于初始化设备，调用方传入的设备对象不满足接口前置条件，无法继续完成本次URMA操作。";
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
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init_member_eid_info_list，Invalid slave device number，of "
           "device。";
}

std::string UrmaFailure028::GetId() const
{
    return "urma_028";
}

} // namespace diag
