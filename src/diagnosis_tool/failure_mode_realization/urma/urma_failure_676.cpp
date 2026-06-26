#include "urma_failure_676.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure676> g_urma("urma_676");

bool UrmaFailure676::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("handle_fake_cr_with_store") != std::string::npos &&
           message.find("Invalid cr error status:") != std::string::npos;
}

std::string UrmaFailure676::GetName() const
{
    return "handle、FAKE、CR状态不满足要求导致handlehandle、FAKE、CR失败";
}

std::string UrmaFailure676::GetRootCauseDesc() const
{
    return "handle_fake_cr_with_"
           "store执行handlehandle、FAKE、CR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure676::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure676::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure676::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_fake_cr_with_store，Invalid cr error status:。";
}

std::string UrmaFailure676::GetId() const
{
    return "urma_676";
}
} // namespace diag
