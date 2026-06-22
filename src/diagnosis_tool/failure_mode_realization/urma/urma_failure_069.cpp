#include "urma_failure_069.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure069> g_urma("urma_069");

bool UrmaFailure069::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_relink_primary_import") != std::string::npos &&
           message.find("Failed to import recreated primary ptjetty, local_idx:") != std::string::npos &&
           message.find("target_idx:") != std::string::npos && message.find("pjetty_id:") != std::string::npos;
}

std::string UrmaFailure069::GetName() const
{
    return "下层资源创建失败导致导入relink、primary失败";
}

std::string UrmaFailure069::GetRootCauseDesc() const
{
    return "bondp_relink_primary_"
           "import在导入relink、primary过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure069::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure069::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure069::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_relink_primary_import，Failed to import recreated primary "
           "ptjetty, local"
           "_idx:，target_idx:，pjetty_id:。";
}

std::string UrmaFailure069::GetId() const
{
    return "urma_069";
}
} // namespace diag
