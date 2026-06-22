#include "urma_failure_066.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure066> g_urma("urma_066");

bool UrmaFailure066::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_post_send_wr_and_store") != std::string::npos &&
           message.find("WR->tjetty is NULL") != std::string::npos;
}

std::string UrmaFailure066::GetName() const
{
    return "工作请求、AND、store状态不满足要求导致投递工作请求、AND、store失败";
}

std::string UrmaFailure066::GetRootCauseDesc() const
{
    return "bondp_post_send_wr_and_"
           "store执行投递工作请求、AND、store时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure066::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure066::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure066::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_send_wr_and_store，WR->tjetty is NULL。";
}

std::string UrmaFailure066::GetId() const
{
    return "urma_066";
}
} // namespace diag
