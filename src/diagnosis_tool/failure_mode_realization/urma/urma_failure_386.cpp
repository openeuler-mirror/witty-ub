#include "urma_failure_386.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure386> g_urma("urma_386");

bool UrmaFailure386::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_post_recv_wr_no_store") != std::string::npos &&
           message.find("Bondp supports at most") != std::string::npos && message.find("wr_list.") != std::string::npos;
}

std::string UrmaFailure386::GetName() const
{
    return "工作请求、NO、store状态不满足要求导致投递工作请求、NO、store失败";
}

std::string UrmaFailure386::GetRootCauseDesc() const
{
    return "bondp_post_recv_wr_no_"
           "store执行投递工作请求、NO、store时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure386::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure386::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure386::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_recv_wr_no_store，Bondp supports at most，wr_list.。";
}

std::string UrmaFailure386::GetId() const
{
    return "urma_386";
}
} // namespace diag
