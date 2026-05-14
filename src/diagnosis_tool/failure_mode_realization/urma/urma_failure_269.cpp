#include "urma_failure_269.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure269> g_urma("urma_269");

bool UrmaFailure269::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_find_vtseg_by_va' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bondp_hash_table_lookup fail')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure269::GetName() const
{
    return "bondp_find_vtseg_by_va 更新 目标 segment 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure269::GetRootCauseDesc() const
{
    return "bondp_find_vtseg_by_va 需要维护 目标 segment "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure269::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure269::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure269::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bondp_hash_table_lookup fail";
}

std::string UrmaFailure269::GetId() const
{
    return "urma_269";
}

} // namespace diag
