#include "urma_failure_204.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure204> g_urma("urma_204");

bool UrmaFailure204::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_import_jfr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to import vjetty, [' | grep -F ']:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure204::GetName() const
{
    return "bondp_import_jfr 执行导入 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure204::GetRootCauseDesc() const
{
    return "bondp_import_jfr 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure204::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure204::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure204::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to import vjetty, []";
}

std::string UrmaFailure204::GetId() const
{
    return "urma_204";
}

} // namespace diag
