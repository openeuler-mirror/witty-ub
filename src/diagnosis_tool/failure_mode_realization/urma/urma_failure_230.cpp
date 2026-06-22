#include "urma_failure_230.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure230> g_urma("urma_230");

bool UrmaFailure230::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("handle_fake_cr_with_store") != std::string::npos &&
           message.find("Skip fake cr because vjetty is not found, idx:") != std::string::npos &&
           message.find(", local_id:") != std::string::npos;
}

std::string UrmaFailure230::GetName() const
{
    return "handle、FAKE、CR状态不满足要求导致handlehandle、FAKE、CR失败";
}

std::string UrmaFailure230::GetRootCauseDesc() const
{
    return "handle_fake_cr_with_"
           "store执行handlehandle、FAKE、CR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure230::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure230::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure230::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_fake_cr_with_store，Skip fake cr because vjetty is not found, "
           "idx:，, lo"
           "cal_id:。";
}

std::string UrmaFailure230::GetId() const
{
    return "urma_230";
}
} // namespace diag
