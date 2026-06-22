#include "urma_failure_319.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure319> g_urma("urma_319");

bool UrmaFailure319::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_unregister_seg_inner") != std::string::npos &&
           message.find("Failed to delete pseg for vseg, token_id:") != std::string::npos &&
           message.find(", handle:") != std::string::npos;
}

std::string UrmaFailure319::GetName() const
{
    return "下层资源删除失败导致注销Segment、inner失败";
}

std::string UrmaFailure319::GetRootCauseDesc() const
{
    return "bondp_unregister_seg_"
           "inner清理Segment、inner时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure319::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure319::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure319::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unregister_seg_inner，Failed to delete pseg for vseg, "
           "token_id:，, handle"
           ":。";
}

std::string UrmaFailure319::GetId() const
{
    return "urma_319";
}
} // namespace diag
