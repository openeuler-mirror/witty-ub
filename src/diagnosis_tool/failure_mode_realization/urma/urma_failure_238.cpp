#include "urma_failure_238.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure238> g_urma("urma_238");

bool UrmaFailure238::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'set_fadd_wr_ptseg_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'when set faa_wr, one of src or dst is NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure238::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure238::GetRootCauseDesc() const
{
    return "set_fadd_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure238::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure238::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure238::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：when set faa_wr, one of src or dst is NULL";
}

std::string UrmaFailure238::GetId() const
{
    return "urma_238";
}

} // namespace diag
