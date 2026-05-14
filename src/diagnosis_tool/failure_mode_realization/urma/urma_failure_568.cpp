#include "urma_failure_568.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure568> g_urma("urma_568");

bool UrmaFailure568::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_import_pjfr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Currently, jfr does not support single-path mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure568::GetName() const
{
    return "bondp_import_pjfr 校验 目标 Jetty 业务条件不满足导致导入流程拒绝继续执行";
}

std::string UrmaFailure568::GetRootCauseDesc() const
{
    return "bondp_import_pjfr 在执行导入时发现 目标 Jetty "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure568::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure568::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure568::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Currently, jfr does not support single-path mode";
}

std::string UrmaFailure568::GetId() const
{
    return "urma_568";
}

} // namespace diag
