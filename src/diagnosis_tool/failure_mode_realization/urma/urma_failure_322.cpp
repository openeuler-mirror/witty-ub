#include "urma_failure_322.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure322> g_urma("urma_322");

bool UrmaFailure322::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_seg") != std::string::npos &&
           message.find("Failed to lookup v2p_token_id, ret:") != std::string::npos;
}

std::string UrmaFailure322::GetName() const
{
    return "导入Segment执行失败导致导入Segment失败";
}

std::string UrmaFailure322::GetRootCauseDesc() const
{
    return "bondp_import_seg执行导入Segment时依赖的导入Segment步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure322::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure322::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure322::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_seg，Failed to lookup v2p_token_id, ret:。";
}

std::string UrmaFailure322::GetId() const
{
    return "urma_322";
}
} // namespace diag
