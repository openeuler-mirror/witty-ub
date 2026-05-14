#include "urma_failure_645.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure645> g_urma("urma_645");

bool UrmaFailure645::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'get_v_conn_on_send' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to create v_conn for vjetty, ret: , [ -> ]')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure645::GetName() const
{
    return "get_v_conn_on_send 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure645::GetRootCauseDesc() const
{
    return "get_v_conn_on_send 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure645::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure645::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure645::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create v_conn for vjetty, ret: , [ -> ]";
}

std::string UrmaFailure645::GetId() const
{
    return "urma_645";
}

} // namespace diag
