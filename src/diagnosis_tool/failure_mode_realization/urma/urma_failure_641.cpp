#include "urma_failure_641.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure641> g_urma("urma_641");

bool UrmaFailure641::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'post_send_check_valid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Data cannot be transferred between jettys in different matrix server mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure641::GetName() const
{
    return "post_send_check_valid 校验 context 业务条件不满足导致投递流程拒绝继续执行";
}

std::string UrmaFailure641::GetRootCauseDesc() const
{
    return "post_send_check_valid 在执行投递时发现 context "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure641::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure641::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure641::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Data cannot be transferred between jettys in different matrix server mode";
}

std::string UrmaFailure641::GetId() const
{
    return "urma_641";
}

} // namespace diag
