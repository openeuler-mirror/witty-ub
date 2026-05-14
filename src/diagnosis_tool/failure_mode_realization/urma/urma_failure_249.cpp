#include "urma_failure_249.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure249> g_urma("urma_249");

bool UrmaFailure249::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_init_ctx_table' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to create p_vjetty_id_table')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure249::GetName() const
{
    return "bondp_init_ctx_table 更新 context 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure249::GetRootCauseDesc() const
{
    return "bondp_init_ctx_table 需要维护 context "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure249::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure249::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure249::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create p_vjetty_id_table";
}

std::string UrmaFailure249::GetId() const
{
    return "urma_249";
}

} // namespace diag
