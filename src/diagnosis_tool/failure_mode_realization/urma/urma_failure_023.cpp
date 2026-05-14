#include "urma_failure_023.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure023> g_urma("urma_023");

bool UrmaFailure023::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'import_jfr_default' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to import jfr, no valid route to rjfr')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure023::GetName() const
{
    return "import_jfr_default 校验 JFR 业务条件不满足导致导入流程拒绝继续执行";
}

std::string UrmaFailure023::GetRootCauseDesc() const
{
    return "import_jfr_default 在执行导入时发现 JFR "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure023::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure023::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure023::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to import jfr, no valid route to rjfr";
}

std::string UrmaFailure023::GetId() const
{
    return "urma_023";
}

} // namespace diag
